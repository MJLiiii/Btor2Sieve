(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x42 (= i_2 s_4)))
(not $x42)))
(check-sat)
