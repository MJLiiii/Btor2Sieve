(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x446 (= i_2 s_6)))
(not $x446)))
(check-sat)
