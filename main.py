import random
import os

class Player:
    def __init__(self, name):
        self.name = name
        self.role = None
        self.is_good = None

    def __str__(self):
        return self.name

class AvalonGame:
    def __init__(self, player_names):
        self.players = [Player(name) for name in player_names]
        self.num_players = len(player_names)
        self.missions = [] # List of mission results
        self.current_mission = 1
        self.failed_votes = 0
        self.leader_index = 0
        
        # Configuration for 5 players (can be expanded)
        # 5 players: 3 good, 2 evil (Merlin, Percival, Servant vs Assassin, Morgana)
        self.mission_sizes = {
            5: [2, 3, 2, 3, 3],
            6: [2, 3, 4, 3, 4],
            7: [2, 3, 3, 4, 4],
            8: [3, 4, 4, 5, 5],
            9: [3, 4, 4, 5, 5],
            10: [3, 4, 4, 5, 5]
        }
    
    def assign_roles(self):
        roles = []
        if self.num_players == 5:
            roles = ["Merlin", "Percival", "Loyal Servant", "Assassin", "Morgana"]
        else:
            # Fallback for now to just generic 5 player
            roles = ["Merlin", "Percival", "Loyal Servant", "Assassin", "Morgana"]
            print("Currently only supports 5 players strictly in this basic version.")
            return False

        random.shuffle(roles)
        for i, player in enumerate(self.players):
            player.role = roles[i]
            player.is_good = player.role in ["Merlin", "Percival", "Loyal Servant"]

        return True

    def show_information(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== 角色确认环节 ===")
        for player in self.players:
            input(f"请 {player.name} 准备查看身份，按回车键继续 (其他玩家请闭眼)...")
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"你的名字: {player.name}")
            print(f"你的角色: {player.role}")
            print(f"阵营: {'好人' if player.is_good else '坏人'}")
            
            # View phase logic
            if player.role == "Merlin":
                evils = [p.name for p in self.players if not p.is_good]
                print(f"你看到了坏人: {', '.join(evils)}")
            elif player.role == "Percival":
                merlin_morgana = [p.name for p in self.players if p.role in ["Merlin", "Morgana"]]
                random.shuffle(merlin_morgana) # Don't reveal who is who
                print(f"你看到了梅林和莫甘娜(不知道谁是谁): {', '.join(merlin_morgana)}")
            elif not player.is_good:
                evils = [p.name for p in self.players if not p.is_good and p != player]
                print(f"你的坏人同伴是: {', '.join(evils)}")
            
            input("请按回车键隐藏身份并传给下一位玩家...")
            os.system('cls' if os.name == 'nt' else 'clear')

    def play(self):
        if not self.assign_roles():
            return

        self.show_information()
        
        while self.current_mission <= 5:
            print(f"\n=== 第 {self.current_mission} 轮任务 ===")
            required_players = self.mission_sizes[self.num_players][self.current_mission - 1]
            print(f"本轮需要 {required_players} 人执行任务。")
            
            leader = self.players[self.leader_index]
            print(f"当前队长是: {leader.name}")
            
            print("队长请选择队员 (输入玩家名字，用空格分隔):")
            for p in self.players:
                print(f"- {p.name}")
                
            chosen_names = input("> ").split()
            team = [p for p in self.players if p.name in chosen_names]
            
            if len(team) != required_players:
                print("人数不正确，请重新选择！")
                continue
                
            print(f"队长 {leader.name} 提出了队伍: {', '.join([p.name for p in team])}")
            print("开始投票 (1:赞成, 0:反对)")
            
            approves = 0
            for p in self.players:
                vote = input(f"{p.name} 的投票: ")
                if vote.strip() == "1":
                    approves += 1
                    
            if approves > self.num_players / 2:
                print(">>> 组队成功！进入任务执行阶段。")
                self.failed_votes = 0
                
                fails = 0
                for member in team:
                    if member.is_good:
                        print(f"{member.name} (好人) 自动投出任务成功。")
                    else:
                        act = input(f"{member.name} (坏人)，请选择 (1:成功, 0:失败): ")
                        if act.strip() == "0":
                            fails += 1
                            
                if fails > 0:
                    print(f"任务失败！出现 {fails} 张失败票。")
                    self.missions.append(False)
                else:
                    print("任务成功！")
                    self.missions.append(True)
                    
                self.current_mission += 1
            else:
                print(">>> 组队失败！")
                self.failed_votes += 1
                if self.failed_votes >= 5:
                    print("连续5次组队失败，坏人阵营获胜！")
                    return
            
            self.leader_index = (self.leader_index + 1) % self.num_players
            
            good_wins = self.missions.count(True)
            evil_wins = self.missions.count(False)
            
            print(f"当前战况 - 好人: {good_wins} 胜, 坏人: {evil_wins} 胜")
            
            if evil_wins >= 3:
                print("坏人阵营累计3次阻挠任务成功，坏人获胜！")
                return
            elif good_wins >= 3:
                print("好人阵营率先完成3次任务，进入刺杀环节！")
                self.assassination_phase()
                return

    def assassination_phase(self):
        print("\n=== 刺杀环节 ===")
        assassin = next(p for p in self.players if p.role == "Assassin")
        print(f"刺客是: {assassin.name}")
        print("请坏人沟通后，刺客输入要刺杀的好人名字:")
        target_name = input("> ").strip()
        
        target = next((p for p in self.players if p.name == target_name), None)
        if target and target.role == "Merlin":
            print("刺客刺杀成功！梅林死了，坏人阵营反败为胜！")
        else:
            print("刺客刺杀失败！好人阵营最终获胜！")

if __name__ == "__main__":
    print("欢迎来到阿瓦隆 (当前为5人基础版终端测试)")
    players_input = input("请输入5名玩家的名字 (用空格分隔): ").split()
    if len(players_input) == 5:
        game = AvalonGame(players_input)
        game.play()
    else:
        print("需要正好5名玩家！")
