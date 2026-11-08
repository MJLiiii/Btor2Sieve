(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x1875 (= s_3 s_4)))
(not $x1875)))
(check-sat)
