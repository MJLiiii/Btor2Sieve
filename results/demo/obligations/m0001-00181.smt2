(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x97 (= i_8 (_ bv15 4))))
(not $x97)))
(check-sat)
