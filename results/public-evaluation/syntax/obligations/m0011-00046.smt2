(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x505 (= i_2 s_4)))
(not $x505)))
(check-sat)
